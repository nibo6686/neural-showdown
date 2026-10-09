import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import test, {after} from 'node:test';
import {Battle, Teams} from 'pokemon-showdown';
import {LocalBattleEnv} from '../src/env_manager';
import {runPipelineEpisode, type PipelineEpisodeOptions} from '../src/pipeline_episode';
import {validatePipelineEpisodeEvidence, sealPipelineEpisodeEvidence, episodeEvidenceContentDigest as digest} from '../src/pipeline_episode_evidence';
import {validateObservableBattleState} from '../src/belief_state';
import {assertPublicItemsMatchEvidence, projectPublicItems, projectPublicItemDispositions, projectPublicOwnedItemHistory} from '../src/public_item';
import {assertPublicItemTamperMatrix, assertTerminalIdentityTamperMatrix, rehash, python, itemIdentityMatrixCounts} from './public_consequence_test_helpers';
import {writeFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fingerprintSimulatorState} from '../src/transition';
import {validatePipelineLinkedRecordBundle} from '../src/pipeline_integration';
import type {PlayerID} from '../src/types';
import {withTerminalOwner, terminalOwnedItems} from '../src/public_health';

after(() => console.log(`C22/C23 canonical adversarial candidates: ${JSON.stringify(itemIdentityMatrixCounts)}`));

test('terminal item authority follows replacement order and ignores owner rows without an item fact', () => {
  const rows = [{slot: 1, ident: 'p1: Actual', name: 'Actual', base_species: 'Zoroark'},
    {slot: 2, ident: 'p1: Disguise', name: 'Disguise', base_species: 'Snorlax'},
    {slot: 3, ident: 'p1: Unknown', name: 'Unknown', base_species: 'Eevee'}];
  const prefix = ['|switch|p1a: Disguise|Snorlax|100/100'];
  const predecessor = {schema_version: 'observable-battle-state/v2', battle_id: 'ordered-authority', perspective: 'p1', protocol_prefix: prefix,
    request: {side: [{ident: 'p1: Actual', active: true, item: 'leftovers'}, {ident: 'p1: Disguise', item: 'sitrusberry'}, {ident: 'p1: Unknown'}]}, view: {self_team: rows}};
  const successor = {...predecessor, request: null, protocol_prefix: [...prefix, '|replace|p1a: Actual|Zoroark|100/100', '|-enditem|p1a: Disguise|Sitrus Berry|[eat]'],
    view: {self_team: structuredClone(rows), terminated: true}};
  withTerminalOwner({predecessor, before: {step_index: 0, branch_id: 'before', state_fingerprint: 'before'},
    transition: {step_index: 0, parent_branch_id: 'before', branch_id: 'after', input_state_fingerprint: 'before', output_state_fingerprint: 'after'},
    after: {step_index: 1, branch_id: 'after', state_fingerprint: 'after'}}, successor, () => {
      assert.deepEqual(terminalOwnedItems(successor.view), {'p1: Actual': 'leftovers', 'p1: Disguise': null});
    });
  assert.equal(terminalOwnedItems(successor.view), undefined);
});

const writers = [
  ['reveal', ['|-item|p1a: One|Air Balloon']],
  ['frisk', ['|-item|p1a: One|Leftovers|[from] ability: Frisk|[of] p2a: Other']],
  ['eat', ['|-enditem|p1a: One|Sitrus Berry|[eat]', '|-heal|p1a: One|67/100|[from] item: Sitrus Berry']],
  ['air-balloon', ['|-item|p1a: One|Air Balloon', '|-enditem|p1a: One|Air Balloon']],
  ['use', ['|-enditem|p1a: One|White Herb']],
  ['remove', ['|-enditem|p1a: One|Leftovers|[from] move: Knock Off|[of] p2a: Other']],
  ['recycle', ['|-enditem|p1a: One|White Herb', '|-item|p1a: One|White Herb|[from] move: Recycle']],
  ['trick', ['|-item|p1a: One|Leftovers|[from] move: Trick', '|-enditem|p1a: One|Leftovers|[silent]|[from] move: Trick']],
  ['switcheroo', ['|-enditem|p1a: One|Leftovers|[silent]|[from] move: Switcheroo', '|-item|p1a: One|Choice Scarf|[from] move: Switcheroo']],
  ['bare', ['|item|p1a: One|Leftovers', '|enditem|p1a: One|Leftovers']],
  ['replace', ['|-enditem|p1a: One|Sitrus Berry|[eat]', '|replace|p1a: Actual|Zoroark, L80|67/100']],
  ['faint-retains', ['|-item|p1a: One|Air Balloon', '|faint|p1a: One']],
  ['switch-unknown', ['|-item|p1a: One|Air Balloon', '|switch|p1a: One|Snorlax, L80|100/100']],
] as const;
for (const [name, suffix] of writers) test(`ordered public item ${name}: known names, absence and unknown`, () => {
  const prefix = ['|switch|p1a: One|Snorlax, L80|100/100', ...suffix];
  const facts = projectPublicItems(prefix);
  for (const perspective of ['p1', 'p2']) {
    const rows: any[] = Object.entries(facts).map(([ident, item]) => ({ident, ...(perspective === 'p1' ? {item, ...projectPublicItemDispositions(prefix)[ident], item_suppressed: false} : item !== null ? {item: 'has-item'} : {})}));
    const team = perspective === 'p1' ? 'self_team' : 'opponent_team';
    const view = {self_team: team === 'self_team' ? rows : [], opponent_team: team === 'opponent_team' ? rows : []};
    assert.doesNotThrow(() => assertPublicItemsMatchEvidence(prefix, perspective, view, null));
    for (const [index, row] of rows.entries()) {
      const bad = structuredClone(view) as any;
      bad[team][index].item = perspective === 'p1' ? row.item ? null : 'leftovers' : row.item ? undefined : 'has-item';
      assert.throws(() => assertPublicItemsMatchEvidence(prefix, perspective, bad, null), /Public item/);
    }
  }
});

test('historical omitted item containers are compatible only without an established possession fact', () => {
  assertPublicItemsMatchEvidence([], 'p2', {}, null);
  const unknown = {self_team: [], opponent_team: [{ident: 'p1: One'}]};
  assertPublicItemsMatchEvidence(['|switch|p1a: One|Snorlax, L80|100/100'], 'p2', unknown, null);
  assert.throws(() => assertPublicItemsMatchEvidence([], 'p2', {self_team: [], opponent_team: [{ident: 'p1: One', item: 'has-item'}]}, null), /no eligible/);
  for (const item of ['|-item|p1a: One|Air Balloon', '|-enditem|p1a: One|Air Balloon']) {
    for (const view of [{}, {opponent_team: false}, {opponent_team: [{}]}, {self_team: [{ident: 'p1: One'}]}]) {
      assert.throws(() => assertPublicItemsMatchEvidence([item], 'p2', view, null), /Public item/);
    }
  }
});

// Full-array sweep encoding exercises the same bulk validator without obscuring source identities.
function sweep(result: any) {
  const histories = ['observation_history', 'simulator_snapshot_history', 'transition_history', 'candidates', 'evidence', 'unresolved', 'contradictions'];
  const beliefs = new Map<string, any>();
  const records = {p1: [], p2: []} as any;
  for (const player of ['p1', 'p2']) for (const bundle of result.records[player]) {
    for (const belief of [bundle.input_belief, bundle.successor_belief]) beliefs.set(belief.belief_id, belief);
    records[player].push({transition_id: bundle.transition.transition_id, action: bundle.action, input_belief_id: bundle.input_belief.belief_id, successor_belief_id: bundle.successor_belief.belief_id});
  }
  return {schema_version: 'pipeline-episode-publication-sweep/v1',
    result: Object.fromEntries(Object.entries(result).filter(([key]) => !['records', 'evidence_envelope'].includes(key))),
    evidence_envelope: result.evidence_envelope, records,
    beliefs: [...beliefs.values()].map((belief) => ({belief_id: belief.belief_id, base_belief_id: null,
      fields: Object.fromEntries(Object.entries(belief).filter(([key]) => !histories.includes(key) && !['belief_id', 'source_protocol_prefix'].includes(key))),
      arrays: Object.fromEntries(histories.map((key) => [key, {mode: 'full', items: belief[key]}]))})),
  };
}
function rehashResult(result: any) {
  const references = new Map<string, any>();
  const observations = new Set<any>();
  function collect(value: any) {
    if (!value || typeof value !== 'object') return;
    if (value.schema_version?.startsWith('observable-battle-state/') && value.view) observations.add(value);
    else for (const child of Object.values(value)) collect(child);
  }
  collect(result);
  for (const observation of observations) {
    const old = observation.observation_id;
    observation.observation_id = `obs-${digest(Object.fromEntries(Object.entries(observation).filter(([key]) => !['observation_id', 'protocol_prefix'].includes(key))))}`;
    references.set(old, observation.observation_id);
  }
  function update(value: any, changes: Map<string, string>) {
    if (!value || typeof value !== 'object') return;
    for (const [key, child] of Object.entries(value)) {
      if (typeof child === 'string' && changes.has(child)) value[key] = changes.get(child);
      else update(child, changes);
    }
  }
  update(result, references);
  const beliefs = new Set<any>();
  for (const player of ['p1', 'p2']) for (const bundle of result.records[player]) {beliefs.add(bundle.input_belief); beliefs.add(bundle.successor_belief);}
  const pending = [...beliefs], changed = new Map<string, string>();
  while (pending.length) {
    const index = pending.findIndex((belief) => !pending.some((parent) => parent.belief_id === belief.parent_belief_id));
    assert.ok(index >= 0);
    const belief = pending.splice(index, 1)[0], old = belief.belief_id;
    update(belief, changed);
    belief.belief_id = `belief-${digest(Object.fromEntries(Object.entries(belief).filter(([key]) => key !== 'belief_id')))}`;
    changed.set(old, belief.belief_id);
  }
  update(result, changed);
  const envelope = result.evidence_envelope;
  result.run_id = envelope.run_id = `episode-${createHash('sha256').update(JSON.stringify({schema: 'pipeline-episode/v1', battle_id: result.battle_id,
    format: result.ruleset, policy: result.policy_id, limits: result.limits, initial_boundary: result.initial_boundary})).digest('hex')}`;
  const identity = {schema_version: envelope.origin.schema_version, run_id: envelope.run_id, battle_id: envelope.battle_id,
    ruleset: envelope.ruleset, source_ref: envelope.source_ref, kind: envelope.origin.kind, boundary: envelope.origin.boundary};
  envelope.origin.origin_id = `episode-origin-${digest(identity)}`;
  for (const commit of envelope.commits) commit.origin_id = envelope.origin.origin_id;
  result.evidence_envelope = sealPipelineEpisodeEvidence(Object.fromEntries(Object.entries(envelope).filter(([key]) => key !== 'evidence_id')) as any);
}

for (const actor of ['p1', 'p2'] as const) for (const shape of ['consume', 'recycle', 'trick', 'switcheroo', 'illusion', 'revealed', 'known-disguise', 'known-consumed'] as const) {
  test(`source ${actor} ${shape}: restored ordinary v1/v2, full envelope/result and bulk semantic matrix`, async () => {
    console.log(`C22/C23 source matrix: ${actor} ${shape}`);
    const illusion = shape === 'illusion' || shape === 'revealed' || shape === 'known-disguise' || shape === 'known-consumed';
    const ownText = shape === 'known-consumed' ? 'Disguise (Snorlax) @ Sitrus Berry\nEVs: 4 HP\nAbility: Immunity\n- Belly Drum\n- Splash\n\nActual (Zoroark) @ Leftovers\nAbility: Illusion\n- Dark Pulse\n- Splash' : shape === 'known-disguise' ? 'Disguise (Snorlax) @ Leftovers\nAbility: Immunity\n- Splash\n\nActual (Zoroark) @ Leftovers\nAbility: Illusion\n- Dark Pulse\n- Splash' : illusion ? 'Actual (Zoroark) @ Leftovers\nAbility: Illusion\n- Dark Pulse\n- Splash\n\nDisguise (Snorlax)\nAbility: Immunity\n- Splash'
      : shape === 'recycle' ? 'Holder (Smeargle) @ White Herb\nAbility: Own Tempo\n- Shell Smash\n- Recycle\n- Tackle'
      : shape === 'trick' || shape === 'switcheroo' ? `Swapper (Rotom) @ Choice Scarf\nAbility: Levitate\n- ${shape === 'trick' ? 'Trick' : 'Switcheroo'}\n- Splash\n- Tackle`
      : 'Eater (Snorlax) @ Sitrus Berry\nEVs: 4 HP\nAbility: Thick Fat\n- Belly Drum\n- Splash\n- Tackle';
    const foeText = shape === 'known-disguise' ? 'Foe (Pikachu)\nLevel: 40\nAbility: Static\n- Quick Attack\n- Splash' : illusion ? 'Foe (Eevee)\nLevel: 1\nAbility: Run Away\n- Tackle\n- Splash' : 'Target (Snorlax) @ Leftovers\nLevel: 1\nAbility: Thick Fat\n- Splash';
    const battle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
    battle.setPlayer('p1', {name: 'One', team: Teams.import(actor === 'p1' ? ownText : foeText)!});
    battle.setPlayer('p2', {name: 'Two', team: Teams.import(actor === 'p2' ? ownText : foeText)!});
    const snapshot = structuredClone(battle.toJSON());
    const restored = Battle.fromJSON(structuredClone(snapshot));
    const old = LocalBattleEnv.prototype.resetWithOptions;
    try {
      LocalBattleEnv.prototype.resetWithOptions = function (options) { return this.resetFromSerialized(structuredClone(snapshot), options); };
      const options: PipelineEpisodeOptions = {battle_id: `item-identity-${actor}-${shape}`, format: 'gen9randombattle', seed: [1,2,3,4], observation_schema_version: 'observable-battle-state/v2',
        limits: {max_transitions: shape === 'illusion' ? 1 : shape === 'revealed' ? 2 : 3}, policy_id: `item-identity-${shape}/v1`,
        action_order: (observation) => {
          const turn = observation.view.turn;
          const choice = observation.perspective === actor ? (shape === 'known-disguise' || shape === 'known-consumed') && turn === 2 ? 'switch 2' : !illusion && turn === 3 ? 'move 3' : shape === 'revealed' && turn === 1 ? 'move 2' : shape === 'recycle' && turn > 1 ? 'move 2' : shape === 'consume' && turn > 1 || (shape === 'trick' || shape === 'switcheroo') && turn > 1 ? 'move 2' : 'move 1'
            : (shape === 'known-disguise' || shape === 'known-consumed') && turn === 2 || shape === 'illusion' || shape === 'known-consumed' ? 'move 2' : 'move 1';
          const legal = observation.request!.legal_actions.actions.find((action) => action?.choice === choice);
          assert.ok(legal, choice); return [legal.index, ...observation.request!.legal_actions.available_indices.filter((index) => index !== legal.index)];
        }};
      const result = await runPipelineEpisode(options);
      assert.equal(result.counts.rejected_candidates, 0, JSON.stringify(result.stop));
      assert.equal(result.counts.committed_transitions, shape === 'illusion' ? 1 : shape === 'revealed' ? 2 : 3);
      for (let turn = 1; turn <= result.counts.committed_transitions; turn++) {
        const ownChoice = (shape === 'known-disguise' || shape === 'known-consumed') && turn === 2 ? 'switch 2' : !illusion && turn === 3 ? 'move 3' : shape === 'revealed' && turn === 1 ? 'move 2' : shape === 'recycle' && turn > 1 ? 'move 2' : shape === 'consume' && turn > 1 || (shape === 'trick' || shape === 'switcheroo') && turn > 1 ? 'move 2' : 'move 1';
        const foeChoice = shape === 'illusion' || shape === 'known-consumed' || shape === 'known-disguise' && turn === 2 ? 'move 2' : 'move 1';
        const choice = actor === 'p1' ? [ownChoice, foeChoice] : [foeChoice, ownChoice];
        battle.makeChoices(...choice); restored.makeChoices(...choice);
      }
      assert.equal(fingerprintSimulatorState(battle.toJSON()), fingerprintSimulatorState(restored.toJSON()));
      if (illusion) {
        assert.equal(result.status, 'completed');
        assert.equal(battle.ended, true);
        assert.equal(battle.log.some((line) => line.startsWith(`|replace|${actor}a: Actual|`)), shape !== 'illusion' && shape !== 'known-consumed');
        if (shape === 'illusion' || shape === 'known-consumed') assertTerminalIdentityTamperMatrix(result.records[actor].at(-1)!);
      }
      const original = JSON.stringify(result);
      validatePipelineEpisodeEvidence(JSON.parse(original).evidence_envelope);
      for (const payload of [result, result.evidence_envelope, sweep(result)]) {
        const valid = python(payload); assert.equal(valid.status, 0, valid.stderr);
      }
      if (!illusion) for (const player of ['p1', 'p2'] as const) for (const bundle of result.records[player]) {
        assertPublicItemTamperMatrix(bundle);

      }
      if (!illusion) {
        const v1 = await runPipelineEpisode({...options, battle_id: `${options.battle_id}-v1`, observation_schema_version: 'observable-battle-state/v1'});
        assert.equal(v1.counts.committed_transitions, 3);
        for (const player of ['p1', 'p2'] as const) for (const bundle of v1.records[player]) assertPublicItemTamperMatrix(bundle);
      }
      const observer = actor === 'p1' ? 'p2' : 'p1';
      for (const player of illusion ? [actor] : [actor, observer]) for (const at of [0, result.evidence_envelope!.commits.length - 1]) {
        for (const mutation of illusion ? ['alias', 'reorder', 'item', 'last-item', 'disposition'] : ['item', 'missing', 'container']) {
          const bad = JSON.parse(original), observation = bad.evidence_envelope.commits[at].boundary.perspectives[player];
          const team = player === actor ? 'self_team' : 'opponent_team';
          const row = observation.view[team].find((p: any) => p.name === (illusion ? 'Actual' : shape === 'consume' ? 'Eater' : shape === 'recycle' ? 'Holder' : 'Swapper'));
          if (mutation === 'alias') row.ident = `${actor}: Disguise`;
          else if (mutation === 'reorder') observation.view.self_team.reverse();
          else if (mutation === 'last-item') row.last_item = 'sitrusberry';
          else if (mutation === 'disposition') row.item_state = 'consumed';
          else if (mutation === 'missing') observation.view[team] = observation.view[team].filter((p: any) => p !== row);
          else if (mutation === 'container') observation.view[team] = {};
          else if (team === 'self_team') row.item = row.item ? null : 'leftovers';
          else if (row.item) delete row.item; else row.item = 'has-item';
          // Also mutate matching actor-bundle observation so every record join stays coherent.
          for (const bundle of bad.records[player]) if (bundle.successor_observation.observation_id === observation.observation_id) bundle.successor_observation = structuredClone(observation);
          for (const bundle of bad.records[player]) if (bundle.input_observation.observation_id === observation.observation_id) bundle.input_observation = structuredClone(observation);
          rehashResult(bad);
          for (const bundle of bad.records[player]) assert.equal(python(bundle, true).status, 0, `${mutation} coherent canonical record identities`);
          const untouched = JSON.stringify(bad);
          assert.throws(() => validatePipelineEpisodeEvidence(bad.evidence_envelope), /Public (health|item)|Typed lifecycle/);
          itemIdentityMatrixCounts.fullResult++; itemIdentityMatrixCounts.envelope++; itemIdentityMatrixCounts.sweep++;
          for (const payload of [bad, bad.evidence_envelope, sweep(bad)]) {
            const invalid = python(payload); assert.equal(invalid.status, 2, invalid.stderr); assert.equal(invalid.stdout, '');
            assert.match(invalid.stderr, /Public (health|item)|Typed lifecycle/);
          }
          assert.equal(JSON.stringify(bad), untouched);
        }
      }
      for (const player of ['p1', 'p2'] as const) {
        const base = result.evidence_envelope!.commits[0].boundary.perspectives[player];
        const unknown = base.view.opponent_team.find((row) => projectPublicItems(base.protocol_prefix)[row.ident.replace(/^(p[12])a: /, '$1: ')] === undefined);
        if (!unknown) continue;
        const bad = JSON.parse(original), observation = bad.evidence_envelope.commits[0].boundary.perspectives[player];
        observation.view.opponent_team.find((row: any) => row.ident === unknown.ident).item = 'has-item';
        for (const bundle of bad.records[player]) {
          if (bundle.successor_observation.observation_id === observation.observation_id) bundle.successor_observation = structuredClone(observation);
          if (bundle.input_observation.observation_id === observation.observation_id) bundle.input_observation = structuredClone(observation);
        }
        rehashResult(bad);
        for (const bundle of bad.records[player]) assert.equal(python(bundle, true).status, 0, 'unknown-presence canonical record joins');
        const before = JSON.stringify(bad);
        assert.throws(() => validatePipelineEpisodeEvidence(bad.evidence_envelope), /Public item/);
        itemIdentityMatrixCounts.fullResult++; itemIdentityMatrixCounts.envelope++; itemIdentityMatrixCounts.sweep++;
        for (const payload of [bad, bad.evidence_envelope, sweep(bad)]) {const rejected = python(payload); assert.equal(rejected.status, 2, rejected.stderr); assert.equal(rejected.stdout, ''); assert.match(rejected.stderr, /Public item/);}
        assert.equal(JSON.stringify(bad), before);
      }
      assert.equal(JSON.stringify(result), original);
    } finally {LocalBattleEnv.prototype.resetWithOptions = old; battle.destroy(); restored.destroy();}
  });
}

for (const actor of ['p1', 'p2'] as const) for (const revealed of [false, true]) {
  test(`Illusion ${actor} revealed=${revealed}: restored continuation binds validated predecessor and rejects joined chain controls`, async () => {
    const {createPipelineIntegrationSession} = await import('../src/pipeline_integration');
    const {continuePipelineEpisode} = await import('../src/pipeline_episode');
    const {createPipelineEpisodeEvidence} = await import('../src/pipeline_episode_evidence');
    const {canonicalActionFromLegalAction} = await import('../src/canonical_action');
    const battle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
    const own = Teams.import('Actual (Zoroark) @ Leftovers\nAbility: Illusion\n- Dark Pulse\n- Splash\n\nDisguise (Snorlax)\nAbility: Immunity\n- Splash')!;
    const foe = Teams.import('Foe (Eevee)\nLevel: 1\nAbility: Run Away\n- Tackle\n- Splash')!;
    battle.setPlayer('p1', {name: 'One', team: actor === 'p1' ? own : foe});
    battle.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? own : foe});
    const snapshot = structuredClone(battle.toJSON()), restored = Battle.fromJSON(structuredClone(snapshot));
    const old = LocalBattleEnv.prototype.resetWithOptions;
    const sessions: any[] = [];
    try {
      LocalBattleEnv.prototype.resetWithOptions = function (options) {return this.resetFromSerialized(structuredClone(snapshot), options);};
      for (let copy = 0; copy < 2; copy++) sessions.push(await createPipelineIntegrationSession({battle_id: `illusion-resume-${actor}-${revealed}`,
        format: 'gen9randombattle', seed: [1,2,3,4], observation_schema_version: 'observable-battle-state/v2'}));
      const boundaries = [sessions[0].boundary], transitions: any[] = [];
      for (let turn = 0; turn < 2; turn++) {
        for (const session of sessions) {
          const actions = Object.fromEntries((['p1', 'p2'] as const).map((player) => {
            const request = session.boundary.perspectives[player].observation.request!;
            const choice = player === actor ? 'move 2' : revealed ? 'move 1' : 'move 2';
            const action = request.legal_actions.actions.find((entry: any) => entry?.choice === choice)!;
            return [player, canonicalActionFromLegalAction(request, action.index)];
          })) as any;
          const result = await session.step(actions);
          if (session === sessions[0]) {
            boundaries.push(result.boundary);
            const {action_id: _action, ...transition} = result.record_bundles.p1.transition;
            transitions.push({transition, actors: ['p1', 'p2']});
          } else assert.deepEqual(result.boundary, sessions[0].boundary);
        }
        const choices = actor === 'p1' ? ['move 2', revealed ? 'move 1' : 'move 2'] : [revealed ? 'move 1' : 'move 2', 'move 2'];
        battle.makeChoices(...choices); restored.makeChoices(...choices);
      }
      const predecessor = createPipelineEpisodeEvidence({run_id: `episode-${'0'.repeat(64)}`, battle_id: `illusion-resume-${actor}-${revealed}`,
        ruleset: 'gen9randombattle', kind: 'fresh_episode', boundaries, transitions})!;
      validatePipelineEpisodeEvidence(predecessor);
      const options = {predecessor_evidence: predecessor, limits: {max_transitions: 1}, policy_id: 'illusion-resumed-win/v1',
        action_order: (observation: any) => {
          const choice = observation.perspective === actor ? 'move 1' : 'move 2';
          const action = observation.request.legal_actions.actions.find((entry: any) => entry?.choice === choice)!;
          return [action.index, ...observation.request.legal_actions.available_indices.filter((index: number) => index !== action.index)];
        }};
      const result = await continuePipelineEpisode(sessions[0], options), twin = await continuePipelineEpisode(sessions[1], options);
      assert.equal(result.status, 'completed', result.stop.reason); assert.deepEqual(result, twin);
      const choices = actor === 'p1' ? ['move 1', 'move 2'] : ['move 2', 'move 1'];
      battle.makeChoices(...choices); restored.makeChoices(...choices); assert.equal(fingerprintSimulatorState(battle.toJSON()), fingerprintSimulatorState(restored.toJSON()));
      const envelope = result.evidence_envelope!;
      assert.equal(envelope.closure!.complete_capture, true); assert.equal(envelope.closure!.origin_coverage, 'original_initial_requests');
      for (const payload of [envelope, result, sweep(result)]) {const valid = python(payload); assert.equal(valid.status, 0, valid.stderr);}
      const original = JSON.stringify(envelope);
      function resealChain(value: any): any {
        if (value.closure?.predecessor) value.closure.predecessor = resealChain(value.closure.predecessor);
        function observations(boundary: any) {
          for (const observation of Object.values(boundary.perspectives) as any[]) observation.observation_id = `obs-${digest(Object.fromEntries(Object.entries(observation).filter(([key]) => !['observation_id', 'protocol_prefix'].includes(key))))}`;
        }
        observations(value.origin.boundary); for (const commit of value.commits) observations(commit.boundary);
        value.origin.origin_id = `episode-origin-${digest({schema_version: value.origin.schema_version, run_id: value.run_id, battle_id: value.battle_id,
          ruleset: value.ruleset, source_ref: value.source_ref, kind: value.origin.kind, boundary: value.origin.boundary})}`;
        for (const commit of value.commits) commit.origin_id = value.origin.origin_id;
        return sealPipelineEpisodeEvidence(Object.fromEntries(Object.entries(value).filter(([key]) => key !== 'evidence_id')) as any);
      }
      const mutations: Record<string, (candidate: any) => void> = {
        missing: (c) => {c.closure.predecessor = null;},
        foreign: (c) => {
          const prior = c.closure.predecessor; prior.battle_id = 'foreign-battle'; prior.source_ref = 'sim-core://foreign-battle';
          for (const boundary of [prior.origin.boundary, ...prior.commits.map((commit: any) => commit.boundary)]) for (const observation of Object.values(boundary.perspectives) as any[]) observation.battle_id = 'foreign-battle';
        },
        reorder: (c) => {c.closure.predecessor.commits.reverse();},
        mismatch: (c) => {const prior = c.closure.predecessor; prior.commits.at(-1).boundary.state_fingerprint = 'f'.repeat(64); prior.commits.at(-1).transition.output_state_fingerprint = 'f'.repeat(64);},
        'missing-owner': (c) => {c.closure.predecessor.origin.boundary.perspectives[actor].request.side = c.closure.predecessor.origin.boundary.perspectives[actor].request.side.filter((row: any) => row.ident !== `${actor}: Actual`);},
        'origin-owner': (c) => {c.origin.boundary.perspectives[actor].view.self_team[0].ident = `${actor}: Foreign`;},
      };
      for (const [name, mutate] of Object.entries(mutations)) {
        let candidate = JSON.parse(original); mutate(candidate); candidate = resealChain(candidate);
        const before = JSON.stringify(candidate);
        itemIdentityMatrixCounts.envelope++;
        assert.throws(() => validatePipelineEpisodeEvidence(candidate), /predecessor|lineage|coverage|Public health|Public item|request/i, name);
        const invalid = python(candidate); assert.equal(invalid.status, 2, `${name}: ${invalid.stderr}`); assert.equal(invalid.stdout, '');
        assert.match(invalid.stderr, /predecessor|gap|coverage|Public health|Public item|request/i);
        assert.equal(JSON.stringify(candidate), before);
        if (name !== 'origin-owner') {
          const candidateResult = structuredClone(result) as any; candidateResult.evidence_envelope = candidate;
          itemIdentityMatrixCounts.fullResult++; itemIdentityMatrixCounts.sweep++;
          for (const [index, payload] of [candidateResult, sweep(candidateResult)].entries()) {
            if (name === 'missing') writeFileSync(`/tmp/c22-c23-missing-predecessor-${actor}-${revealed}-${index}.json`, JSON.stringify(payload));
            const rejected = python(payload); assert.equal(rejected.status, 2, `${name}: ${rejected.stderr}`); assert.equal(rejected.stdout, '');
            assert.match(rejected.stderr, /predecessor|gap|coverage|Public health|Public item|request/i);
          }
        }
        if (!revealed) assert.throws(() => validateObservableBattleState(candidate.commits.at(-1).boundary.perspectives[actor]), /Public health/, 'rejected envelopes leave no terminal alias authority');
      }
      assert.equal(JSON.stringify(envelope), original);
    } finally {LocalBattleEnv.prototype.resetWithOptions = old; for (const session of sessions) await session.close(); battle.destroy(); restored.destroy();}
  });
}

for (const actor of ['p1', 'p2'] as const) test(`owned ${actor} consumption-switch-reentry retains valid restoration and publication`, async () => {
  const own = 'Eater (Snorlax) @ Sitrus Berry\nEVs: 4 HP\nAbility: Thick Fat\n- Belly Drum\n- Splash\n- Tackle\n\nBench (Eevee)\nAbility: Run Away\n- Splash';
  const foe = 'Target (Snorlax)\nLevel: 1\nAbility: Thick Fat\n- Splash';
  const battle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  battle.setPlayer('p1', {name: 'One', team: Teams.import(actor === 'p1' ? own : foe)!});
  battle.setPlayer('p2', {name: 'Two', team: Teams.import(actor === 'p2' ? own : foe)!});
  const snapshot = structuredClone(battle.toJSON()), restored = Battle.fromJSON(structuredClone(snapshot));
  const old = LocalBattleEnv.prototype.resetWithOptions;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (options) {return this.resetFromSerialized(structuredClone(snapshot), options);};
    for (const schema of ['observable-battle-state/v1', 'observable-battle-state/v2'] as const) {
      const result = await runPipelineEpisode({battle_id: `item-reentry-${actor}-${schema}`, format: 'gen9randombattle', seed: [1,2,3,4], observation_schema_version: schema,
        limits: {max_transitions: 4}, policy_id: 'item-reentry/v1', action_order: (observation) => {
          const turn = observation.view.turn, choice = observation.perspective !== actor ? 'move 1' : turn === 2 ? 'switch 2' : turn === 3 ? 'switch 2' : turn === 4 ? 'move 3' : 'move 1';
          const legal = observation.request!.legal_actions.actions.find((action) => action?.choice === choice)!;
          assert.ok(legal, choice); return [legal.index, ...observation.request!.legal_actions.available_indices.filter((index) => index !== legal.index)];
        }});
      assert.equal(result.status, 'completed', JSON.stringify(result.stop)); assert.equal(result.counts.committed_transitions, 4);
      for (const player of ['p1', 'p2'] as const) for (const bundle of result.records[player]) {const valid = python(bundle); assert.equal(valid.status, 0, valid.stderr);}
      if (schema === 'observable-battle-state/v2') for (const payload of [result, result.evidence_envelope, sweep(result)]) {const valid = python(payload); assert.equal(valid.status, 0, valid.stderr);}
      for (const bundle of result.records[actor]) for (const which of ['input', 'successor']) for (const field of ['last_item', 'item_state']) {
        const originalRow = (bundle as any)[`${which}_observation`].view.self_team.find((row: any) => row.name === 'Eater');
        if (!originalRow.last_item || field === 'item_state' && originalRow.item !== null) continue;
        const bad = structuredClone(bundle) as any, row = bad[`${which}_observation`].view.self_team.find((row: any) => row.name === 'Eater');
        row[field] = field === 'last_item' ? null : 'unknown'; rehash(bad); itemIdentityMatrixCounts.ordinary++;
        assert.equal(python(bad, true).status, 0, 'history omission canonical joins');
        const unchanged = JSON.stringify(bad);
        assert.throws(() => validatePipelineLinkedRecordBundle(bad), /Public item evidence mismatch/);
        const rejected = python(bad); assert.equal(rejected.status, 2, rejected.stderr); assert.equal(rejected.stdout, ''); assert.match(rejected.stderr, /Public item evidence mismatch/);
        assert.equal(JSON.stringify(bad), unchanged);
      }
      if (schema === 'observable-battle-state/v2') for (const at of [1, 2, 3]) for (const field of ['last_item', 'item_state']) {
        const bad = JSON.parse(JSON.stringify(result)), observation = bad.evidence_envelope.commits[at].boundary.perspectives[actor];
        observation.view.self_team.find((row: any) => row.name === 'Eater')[field] = field === 'last_item' ? null : 'unknown';
        for (const bundle of bad.records[actor]) for (const which of ['input', 'successor']) if (bundle[`${which}_observation`].observation_id === observation.observation_id) bundle[`${which}_observation`] = structuredClone(observation);
        rehashResult(bad); for (const bundle of bad.records[actor]) assert.equal(python(bundle, true).status, 0);
        const unchanged = JSON.stringify(bad);
        assert.throws(() => validatePipelineEpisodeEvidence(bad.evidence_envelope, bad.records), /Public item evidence mismatch/);
        for (const payload of [bad, bad.evidence_envelope, sweep(bad)]) {const rejected = python(payload); assert.equal(rejected.status, 2, rejected.stderr); assert.equal(rejected.stdout, ''); assert.match(rejected.stderr, /Public item evidence mismatch/);}
        itemIdentityMatrixCounts.fullResult++; itemIdentityMatrixCounts.envelope++; itemIdentityMatrixCounts.sweep++;
        assert.equal(JSON.stringify(bad), unchanged);
      }
      const final = result.records[actor].at(-1)!.successor_observation;
      assert.equal(final.view.self_team.find((row) => row.name === 'Eater')!.item, null);
      assert.ok(final.protocol_prefix.some((line) => line.startsWith(`|-enditem|${actor}a: Eater|Sitrus Berry|[eat]`)));
    }
    for (const choice of [['move 1', 'move 1'], ['switch 2', 'move 1'], ['switch 2', 'move 1'], ['move 3', 'move 1']]) {
      const choices = actor === 'p1' ? choice : [...choice].reverse(); battle.makeChoices(...choices); restored.makeChoices(...choices);
    }
    assert.equal(fingerprintSimulatorState(battle.toJSON()), fingerprintSimulatorState(restored.toJSON()));
  } finally {LocalBattleEnv.prototype.resetWithOptions = old; battle.destroy(); restored.destroy();}
});

for (const actor of ['p1', 'p2'] as const) for (const revealed of [false, true]) test(`owned ${actor} ${revealed ? 'revealed' : 'unrevealed'} Illusion consumption departure and reentry keeps historical carrier unknown`, async () => {
  console.log(`C22/C23 historical Illusion ${actor}: native source and restored publication`);
  const own = 'Actual (Zoroark) @ Sitrus Berry\nEVs: 4 HP\nAbility: Illusion\n- Belly Drum\n- Splash\n- Dark Pulse\n\nBench (Eevee)\nAbility: Run Away\n- Splash\n\nDisguise (Snorlax) @ Sitrus Berry\nAbility: Immunity\n- Splash';
  const foe = 'Target (Eevee)\nLevel: 1\nAbility: Run Away\n- Splash\n- Quick Attack';
  const battle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  battle.setPlayer('p1', {name: 'One', team: Teams.import(actor === 'p1' ? own : foe)!});
  battle.setPlayer('p2', {name: 'Two', team: Teams.import(actor === 'p2' ? own : foe)!});
  const snapshot = structuredClone(battle.toJSON()), restored = Battle.fromJSON(structuredClone(snapshot));
  const old = LocalBattleEnv.prototype.resetWithOptions, oldSerialize = LocalBattleEnv.prototype.serializeBattle;
  let terminalSnapshot: Record<string, any> | undefined;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (options) {return this.resetFromSerialized(structuredClone(snapshot), options);};
    LocalBattleEnv.prototype.serializeBattle = function () {const value = oldSerialize.call(this); if (value.ended) terminalSnapshot = structuredClone(value); return value;};
    for (const schema of ['observable-battle-state/v1', 'observable-battle-state/v2'] as const) {
      const result = await runPipelineEpisode({battle_id: `item-uncertain-${actor}-${revealed}-${schema}`, format: 'gen9randombattle', seed: [1,2,3,4], observation_schema_version: schema,
        limits: {max_transitions: 4}, policy_id: 'item-uncertain/v1', action_order: (observation) => {
          const turn = observation.view.turn, choice = observation.perspective !== actor ? revealed && turn === 4 ? 'move 2' : 'move 1' : turn === 2 || turn === 3 ? 'switch 2' : turn === 4 ? 'move 3' : 'move 1';
          const legal = observation.request!.legal_actions.actions.find((action) => action?.choice === choice)!;
          assert.ok(legal, choice); return [legal.index, ...observation.request!.legal_actions.available_indices.filter((index) => index !== legal.index)];
        }});
      assert.equal(result.status, 'completed', JSON.stringify(result.stop)); assert.equal(result.counts.committed_transitions, 4);
      for (const player of ['p1', 'p2'] as const) for (const bundle of result.records[player]) {const valid = python(bundle); assert.equal(valid.status, 0, valid.stderr);}
      const foreignAlias = structuredClone(result.records[actor][0]) as any;
      for (const which of ['input', 'successor']) {
        const observation = foreignAlias[`${which}_observation`];
        observation.protocol_prefix = observation.protocol_prefix.map((line: string) => line.replaceAll(`${actor}a: Disguise`, `${actor}a: Foreign`));
        observation.protocol_prefix_hash = digest(observation.protocol_prefix);
        foreignAlias[`${which}_belief`].source_protocol_prefix = [...observation.protocol_prefix];
      }
      rehash(foreignAlias); itemIdentityMatrixCounts.ordinary++;
      assert.equal(python(foreignAlias, true).status, 0, 'foreign appearance canonical identities');
      const foreignUnchanged = JSON.stringify(foreignAlias);
      assert.throws(() => validateObservableBattleState(foreignAlias.input_observation), /owned appearance lacks legitimate Illusion roster authority/);
      const rejectedForeign = python(foreignAlias); assert.equal(rejectedForeign.status, 2, rejectedForeign.stderr); assert.equal(rejectedForeign.stdout, '');
      assert.match(rejectedForeign.stderr, /owned appearance lacks legitimate Illusion roster authority/);
      assert.equal(JSON.stringify(foreignAlias), foreignUnchanged);
      const aliasForgery = structuredClone(result.records[actor][0]) as any;
      for (const which of ['input', 'successor']) {
        const observation = aliasForgery[`${which}_observation`];
        const owner = observation.request.side.find((row: any) => row.active);
        const row = observation.view.self_team.find((row: any) => row.name === 'Actual');
        owner.ability = owner.base_ability = row.ability = row.base_ability = 'immunity';
      }
      rehash(aliasForgery); itemIdentityMatrixCounts.ordinary++;
      assert.equal(python(aliasForgery, true).status, 0, 'alias forgery canonical joins');
      const unchanged = JSON.stringify(aliasForgery);
      assert.throws(() => validateObservableBattleState(aliasForgery.input_observation), /owned appearance lacks legitimate Illusion roster authority/);
      const rejectedAlias = python(aliasForgery); assert.equal(rejectedAlias.status, 2, rejectedAlias.stderr); assert.equal(rejectedAlias.stdout, '');
      assert.match(rejectedAlias.stderr, /owned appearance lacks legitimate Illusion roster authority/);
      assert.equal(JSON.stringify(aliasForgery), unchanged);
      if (schema === 'observable-battle-state/v2') {
        const bad = JSON.parse(JSON.stringify(result));
        const origin = bad.evidence_envelope.origin.boundary.perspectives[actor];
        const owner = origin.request.side.find((row: any) => row.active), row = origin.view.self_team.find((row: any) => row.name === 'Actual');
        owner.ability = owner.base_ability = row.ability = row.base_ability = 'immunity';
        bad.records[actor][0].input_observation = structuredClone(origin);
        rehashResult(bad); assert.equal(python(bad.records[actor][0], true).status, 0);
        const unchangedFull = JSON.stringify(bad);
        assert.throws(() => validatePipelineEpisodeEvidence(bad.evidence_envelope, bad.records), /owned appearance lacks legitimate Illusion roster authority/);
        for (const payload of [bad, bad.evidence_envelope, sweep(bad)]) {
          const rejected = python(payload); assert.equal(rejected.status, 2, rejected.stderr); assert.equal(rejected.stdout, '');
          assert.match(rejected.stderr, /owned appearance lacks legitimate Illusion roster authority/);
        }
        itemIdentityMatrixCounts.fullResult++; itemIdentityMatrixCounts.envelope++; itemIdentityMatrixCounts.sweep++;
        assert.equal(JSON.stringify(bad), unchangedFull);
      }
      const final = result.records[actor].at(-1)!.successor_observation;
      const terminal = new LocalBattleEnv(`historical-restored-${actor}-${revealed}`, 'gen9randombattle', [1,2,3,4]);
      try {
        const restoredTerminal = await terminal.resetFromSerialized(structuredClone(terminalSnapshot!));
        for (const row of final.view.self_team) {
          const restoredRow = restoredTerminal.views[actor]!.self_team.find((entry) => entry.name === row.name)!;
          for (const field of ['active', 'item', 'last_item', 'item_state', 'hp_text', 'hp_ratio'] as const) assert.equal(restoredRow[field], row[field], `${row.name}/${field}`);
        }
      } finally {await terminal.close();}
      assert.equal(final.view.self_team.find((row) => row.name === 'Disguise')!.last_item, null, 'later reveal does not identify earlier consumption carrier');
      const departed = result.records[actor][1].successor_observation;
      assert.equal(departed.view.self_team.find((row) => row.name === 'Actual')!.last_item, null);
      assert.equal(departed.view.self_team.find((row) => row.name === 'Disguise')!.last_item, null);
      assert.equal(departed.view.self_team.find((row) => row.name === 'Disguise')!.item, 'sitrusberry');
      if (schema === 'observable-battle-state/v2') for (const payload of [result, result.evidence_envelope, sweep(result)]) {const valid = python(payload); assert.equal(valid.status, 0, valid.stderr);}
    }
    for (const choice of [['move 1', 'move 1'], ['switch 2', 'move 1'], ['switch 2', 'move 1'], ['move 3', revealed ? 'move 2' : 'move 1']]) {
      const choices = actor === 'p1' ? choice : [...choice].reverse(); battle.makeChoices(...choices); restored.makeChoices(...choices);
    }
    assert.ok(battle.log.some((line) => line.startsWith(`|-enditem|${actor}a: Disguise|Sitrus Berry|[eat]`)));
    assert.equal(battle.log.some((line) => line.startsWith(`|replace|${actor}a: Actual|`)), revealed);
    assert.equal(fingerprintSimulatorState(battle.toJSON()), fingerprintSimulatorState(restored.toJSON()));
  } finally {LocalBattleEnv.prototype.resetWithOptions = old; LocalBattleEnv.prototype.serializeBattle = oldSerialize; battle.destroy(); restored.destroy();}
});

for (const actor of ['p1', 'p2'] as const) test(`source ${actor} forced switch entry-hazard terminal preserves private restoration`, async () => {
  console.log(`C22/C23 forced terminal ${actor}: native source and restoration`);
  const own = Teams.import('Fragile (Eevee)\nLevel: 1\nAbility: Run Away\n- Splash\n\nLead (Snorlax)\nAbility: Immunity\n- Memento')!;
  const foe = Teams.import('Foe (Smeargle)\nAbility: Own Tempo\n- False Swipe\n- Spikes\n- Splash')!;
  const battle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  battle.setPlayer('p1', {team: actor === 'p1' ? own : foe}); battle.setPlayer('p2', {team: actor === 'p2' ? own : foe});
  for (const choices of [['move 1', 'move 1'], ['switch 2', 'move 2'], ['move 1', 'move 3']]) battle.makeChoices(...(actor === 'p1' ? choices : [...choices].reverse()));
  const snapshot = structuredClone(battle.toJSON());
  assert.equal(battle.sides[actor === 'p1' ? 0 : 1].active[0].fainted, true);
  const old = LocalBattleEnv.prototype.resetWithOptions, oldSerialize = LocalBattleEnv.prototype.serializeBattle;
  let terminalSnapshot: Record<string, any> | undefined;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (options) {return this.resetFromSerialized(structuredClone(snapshot), options);};
    LocalBattleEnv.prototype.serializeBattle = function () {const value = oldSerialize.call(this); if (value.ended) terminalSnapshot = structuredClone(value); return value;};
    for (const schema of ['observable-battle-state/v1', 'observable-battle-state/v2'] as const) {
      const result = await runPipelineEpisode({battle_id: `forced-terminal-${actor}-${schema}`, format: 'gen9randombattle', seed: [1,2,3,4], observation_schema_version: schema, limits: {max_transitions: 1}});
      assert.equal(result.status, 'completed', JSON.stringify(result.stop)); assert.equal(result.records[actor].length, 1);
      assert.equal(result.records[actor === 'p1' ? 'p2' : 'p1'].length, 0);
      const final = result.records[actor][0].successor_observation, row = final.view.self_team.find((row) => row.name === 'Fragile')!;
      assert.equal(row.fainted, true); assert.equal(row.active, false);
      const valid = python(result.records[actor][0]); assert.equal(valid.status, 0, valid.stderr);
      const terminal = new LocalBattleEnv(`forced-restored-${actor}`, 'gen9randombattle', [1,2,3,4]);
      try {
        assert.equal(terminalSnapshot?.__neural_terminal_request_history.schema_version, 'terminal-request-history/v2');
        assert.equal(terminalSnapshot?.__neural_terminal_request_history.submitted_switches[actor].force_switch, true);
        const restored = await terminal.resetFromSerialized(structuredClone(terminalSnapshot!));
        const restoredRow = restored.views[actor]!.self_team.find((row) => row.name === 'Fragile')!;
        for (const field of ['active', 'fainted', 'item', 'hp_text', 'last_item', 'item_state'] as const) assert.equal(restoredRow[field], row[field], field);
        for (const offset of [-1, 1, 100_000]) {const bad: Record<string, any> = structuredClone(terminalSnapshot!); bad.__neural_terminal_request_history.submitted_switches[actor].cursor += offset; await assert.rejects(terminal.resetFromSerialized(bad), /exact source choice boundary/);}
      } finally {await terminal.close();}
      if (schema === 'observable-battle-state/v2') for (const payload of [result, result.evidence_envelope]) {const published = python(payload); assert.equal(published.status, 0, published.stderr);}
    }
  } finally {LocalBattleEnv.prototype.resetWithOptions = old; LocalBattleEnv.prototype.serializeBattle = oldSerialize; battle.destroy();}
});

for (const actor of ['p1', 'p2'] as const) test(`source ${actor} waiting boundary cannot erase established owned item authority`, async () => {
  console.log(`C22/C23 waiting authority ${actor}: source capture and semantic negatives`);
  const own = Teams.import('Lead (Snorlax)\nAbility: Immunity\n- Memento\n\nPawmot\n- Revival Blessing\n- Splash')!;
  const foe = Teams.import('Watcher (Snorlax) @ Leftovers\nAbility: Immunity\n- Splash\n- Memento')!;
  const battle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  battle.setPlayer('p1', {team: actor === 'p1' ? own : foe}); battle.setPlayer('p2', {team: actor === 'p2' ? own : foe});
  const snapshot = structuredClone(battle.toJSON()), old = LocalBattleEnv.prototype.resetWithOptions;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (options) {return this.resetFromSerialized(structuredClone(snapshot), options);};
    const result = await runPipelineEpisode({battle_id: `wait-authority-${actor}`, format: 'gen9randombattle', seed: [1,2,3,4], observation_schema_version: 'observable-battle-state/v2',
      limits: {max_transitions: 4}, policy_id: 'wait-authority/v1', action_order: (observation) => {
        const choice = observation.perspective !== actor && observation.view.turn === 2 ? 'move 2' : 'move 1';
        const legal = observation.request!.legal_actions.actions.find((action) => action?.choice === choice) || observation.request!.legal_actions.actions.find((action) => action?.choice === 'switch 2')!;
        assert.ok(legal); return [legal.index, ...observation.request!.legal_actions.available_indices.filter((index) => index !== legal.index)];
      }});
    assert.equal(result.counts.committed_transitions, 4, JSON.stringify(result.stop)); assert.equal(result.status, 'completed');
    const waiting = actor === 'p1' ? 'p2' : 'p1', envelope = result.evidence_envelope!;
    const observation = envelope.commits.find((commit) => commit.boundary.perspectives[waiting].request?.wait)!.boundary.perspectives[waiting];
    assert.equal(observation.request?.wait, true); assert.equal(observation.request?.side.length, 1); assert.equal(observation.request?.side[0].item, 'leftovers');
    for (const payload of [result, envelope, sweep(result)]) {const valid = python(payload); assert.equal(valid.status, 0, valid.stderr);}
    for (const mutation of ['missing-roster', 'missing-roster-and-false-item', 'false-item']) {
      const bad = JSON.parse(JSON.stringify(result)), candidate = bad.evidence_envelope.commits.find((commit: any) => commit.boundary.perspectives[waiting].request?.wait).boundary.perspectives[waiting];
      if (mutation.startsWith('missing-roster')) candidate.request.side = [];
      if (mutation !== 'missing-roster') candidate.view.self_team[0].item = null;
      for (const bundle of bad.records[waiting]) for (const which of ['input', 'successor']) if (bundle[`${which}_observation`].observation_id === candidate.observation_id) bundle[`${which}_observation`] = structuredClone(candidate);
      rehashResult(bad); for (const player of ['p1', 'p2']) for (const bundle of bad.records[player]) assert.equal(python(bundle, true).status, 0);
      const unchanged = JSON.stringify(bad); assert.throws(() => validatePipelineEpisodeEvidence(bad.evidence_envelope, bad.records), /Public item evidence mismatch/);
      for (const payload of [bad, bad.evidence_envelope, sweep(bad)]) {const rejected = python(payload); assert.equal(rejected.status, 2, rejected.stderr); assert.equal(rejected.stdout, ''); assert.match(rejected.stderr, /Public item evidence mismatch/);}
      itemIdentityMatrixCounts.fullResult++; itemIdentityMatrixCounts.envelope++; itemIdentityMatrixCounts.sweep++;
      assert.equal(JSON.stringify(bad), unchanged);
    }
  } finally {LocalBattleEnv.prototype.resetWithOptions = old; battle.destroy();}
});

test('source turn-1000 terminal switches preserve visible owned identity and reject insufficient base authority', async () => {
  console.log('C22/C23 short turn-limit: native preterminal replay');
  const {createPipelineIntegrationSession} = await import('../src/pipeline_integration');
  const {continuePipelineEpisode} = await import('../src/pipeline_episode');
  const {validatePipelineLinkedRecordBundle} = await import('../src/pipeline_integration');
  const options = {battle_id: 'short-source-auto-tie', format: 'gen9randombattle', seed: [31,37,41,43]} as const;
  const initial = await createPipelineIntegrationSession(options);
  const battle = Battle.fromJSON((initial as any).environment.serializeBattle()); await initial.close();
  for (let turn = 1; turn < 999; turn++) battle.makeChoices(...battle.sides.map((side) => `switch ${side.pokemon.findIndex((pokemon) => !pokemon.isActive && !pokemon.fainted) + 1}`));
  assert.equal(battle.turn, 999); assert.equal(battle.ended, false);
  const snapshot = structuredClone(battle.toJSON()), restored = Battle.fromJSON(structuredClone(snapshot));
  const old = LocalBattleEnv.prototype.resetWithOptions;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (opts) {return this.resetFromSerialized(structuredClone(snapshot), opts);};
    for (const schema of ['observable-battle-state/v1', 'observable-battle-state/v2'] as const) {
      console.log(`C22/C23 short turn-limit: ${schema} terminal and publication guards`);
      const session = await createPipelineIntegrationSession({...options, observation_schema_version: schema});
      const result = await continuePipelineEpisode(session, {limits: {max_transitions: 1}, policy_id: 'short-source-auto-tie/v1', action_order: (observation) => {
        const action = observation.request!.legal_actions.actions.find((entry) => entry?.choice.startsWith('switch '))!;
        return [action.index, ...observation.request!.legal_actions.available_indices.filter((index) => index !== action.index)];
      }});
      assert.equal(result.status, 'completed', JSON.stringify(result.stop)); assert.equal(result.counts.committed_transitions, 1);
      for (const player of ['p1', 'p2'] as const) {
        const bundle = result.records[player][0], valid = python(bundle); assert.equal(valid.status, 0, valid.stderr);
        assert.doesNotThrow(() => validatePipelineLinkedRecordBundle(JSON.parse(JSON.stringify(bundle))));
        for (const field of ['active', 'item', 'missing-base', 'illusion-base', 'illusion-current']) {
          const bad = structuredClone(bundle) as any;
          if (field === 'active') bad.successor_observation.view.self_team[0].active = !bad.successor_observation.view.self_team[0].active;
          else if (field === 'item') bad.successor_observation.view.self_team[0].item = bad.successor_observation.view.self_team[0].item ? null : 'leftovers';
          else {
            const owner = bad.input_observation.request.side[0], row = bad.input_observation.view.self_team[0];
            if (field === 'missing-base') {owner.base_ability = null; row.base_ability = null;}
            else if (field === 'illusion-base') {owner.base_ability = 'illusion'; row.base_ability = null;}
            else {owner.ability = row.ability = 'illusion';}
          }
          rehash(bad); itemIdentityMatrixCounts.ordinary++;
          assert.equal(python(bad, true).status, 0, field);
          const before = JSON.stringify(bad);
          if (field.includes('base') || field === 'illusion-current') {
            // The submitted switch proves the incoming owner even when the
            // roster cannot establish that every ability excludes Illusion.
            assert.doesNotThrow(() => validatePipelineLinkedRecordBundle(bad));
            assert.equal(python(bad).status, 0, field);
            const transition = bad.transition;
            assert.throws(() => withTerminalOwner({predecessor: bad.input_observation,
              before: {step_index: transition.step_index, branch_id: transition.parent_branch_id, state_fingerprint: transition.input_state_fingerprint}, transition,
              after: {step_index: transition.step_index + 1, branch_id: transition.branch_id, state_fingerprint: transition.output_state_fingerprint}},
              bad.successor_observation, () => validateObservableBattleState(bad.successor_observation)), /Public health.*sufficient owned identity authority/);
            assert.equal(JSON.stringify(bad), before);
            continue;
          }
          assert.throws(() => validatePipelineLinkedRecordBundle(bad), /Public (health|item)/);
          const rejected = python(bad); assert.equal(rejected.status, 2, `${field}: ${rejected.stderr}`); assert.equal(rejected.stdout, '');
          assert.match(rejected.stderr, /Public (health|item)/); assert.equal(JSON.stringify(bad), before);
        }
      }
      if (schema === 'observable-battle-state/v2') {
        assert.equal(result.evidence_envelope!.closure!.origin_coverage, 'segment_only');
        for (const payload of [result, result.evidence_envelope]) {const valid = python(payload); assert.equal(valid.status, 0, valid.stderr);}
        for (const player of ['p1', 'p2'] as const) for (const field of ['missing-base', 'illusion-base', 'illusion-current']) {
          const bad = JSON.parse(JSON.stringify(result));
          const origin = bad.evidence_envelope.origin.boundary.perspectives[player], owner = origin.request.side[0], row = origin.view.self_team[0];
          if (field === 'missing-base') owner.base_ability = row.base_ability = null;
          else if (field === 'illusion-base') {owner.base_ability = 'illusion'; row.base_ability = null;}
          else owner.ability = row.ability = 'illusion';
          bad.records[player][0].input_observation = structuredClone(origin); rehashResult(bad);
          assert.equal(python(bad.records[player][0], true).status, 0);
          const unchanged = JSON.stringify(bad);
          assert.throws(() => validatePipelineEpisodeEvidence(bad.evidence_envelope), /sufficient owned identity authority/);
          const rejected = python(bad.evidence_envelope); assert.equal(rejected.status, 2, rejected.stderr); assert.equal(rejected.stdout, ''); assert.match(rejected.stderr, /sufficient owned identity authority/);
          itemIdentityMatrixCounts.envelope++;
          assert.doesNotThrow(() => validatePipelineEpisodeEvidence(bad.evidence_envelope, bad.records));
          writeFileSync(`/tmp/c22-c23-normal-terminal-${player}-${field}.json`, JSON.stringify(bad));
          console.log(`C22/C23 short turn-limit: action-bound full ${player} ${field}, ${origin.protocol_prefix.length} prefix records`);
          const started = Date.now(), valid = python(bad); assert.equal(valid.status, 0, valid.stderr);
          console.log(`C22/C23 short turn-limit: action-bound full completed ${Date.now() - started}ms`);
          assert.equal(JSON.stringify(bad), unchanged);
        }
        const segment = python(sweep(result)); assert.equal(segment.status, 2); assert.equal(segment.stdout, '');
        assert.match(segment.stderr, /original-to-terminal chain/);
      }
    }
    const choices = battle.sides.map((side) => `switch ${side.pokemon.findIndex((pokemon) => !pokemon.isActive && !pokemon.fainted) + 1}`);
    battle.makeChoices(...choices); restored.makeChoices(...choices); assert.equal(fingerprintSimulatorState(battle.toJSON()), fingerprintSimulatorState(restored.toJSON())); assert.equal(battle.ended, true);
  } finally {LocalBattleEnv.prototype.resetWithOptions = old; battle.destroy(); restored.destroy();}
});

for (const actor of ['p1', 'p2'] as const) test(`source ${actor} incoming unrevealed terminal Illusion uses the canonical switch action`, async () => {
  console.log(`C22/C23 incoming Illusion: ${actor} native source`);
  const {validatePipelineLinkedRecordBundle} = await import('../src/pipeline_integration');
  const {canonicalActionFromLegalAction} = await import('../src/canonical_action');
  const own = Teams.import('Lead (Eevee)\nAbility: Run Away\n- Splash\n\nActual (Zoroark-Hisui) @ Leftovers\nAbility: Illusion\n- Splash\n\nDisguise (Snorlax) @ Sitrus Berry\nAbility: Immunity\n- Splash')!;
  const foe = Teams.import('Foe (Electrode)\nAbility: Soundproof\n- Explosion')!;
  const battle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  battle.setPlayer('p1', {name: 'One', team: actor === 'p1' ? own : foe});
  battle.setPlayer('p2', {name: 'Two', team: actor === 'p2' ? own : foe});
  const snapshot = structuredClone(battle.toJSON()), restored = Battle.fromJSON(structuredClone(snapshot));
  const old = LocalBattleEnv.prototype.resetWithOptions, oldSerialize = LocalBattleEnv.prototype.serializeBattle;
  let terminalSnapshot: Record<string, any> | undefined;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function (options) {return this.resetFromSerialized(structuredClone(snapshot), options);};
    LocalBattleEnv.prototype.serializeBattle = function () {
      const value = oldSerialize.call(this);
      if (value.ended) terminalSnapshot = structuredClone(value);
      return value;
    };
    for (const schema of ['observable-battle-state/v1', 'observable-battle-state/v2'] as const) {
      console.log(`C22/C23 incoming Illusion: ${actor} ${schema} ordinary matrix`);
      const result = await runPipelineEpisode({battle_id: `incoming-illusion-${actor}-${schema.endsWith('v2') ? 'v2' : 'v1'}`, format: 'gen9randombattle', seed: [1,2,3,4],
        observation_schema_version: schema, limits: {max_transitions: 1}, policy_id: 'incoming-illusion/v1', action_order: (observation) => {
          const choice = observation.perspective === actor ? 'switch 2' : 'move 1';
          const action = observation.request!.legal_actions.actions.find((entry) => entry?.choice === choice)!;
          return [action.index, ...observation.request!.legal_actions.available_indices.filter((index) => index !== action.index)];
        }});
      assert.equal(result.status, 'completed', JSON.stringify(result.stop));
      assert.equal(result.counts.committed_transitions, 1);
      const bundle = result.records[actor][0];
      assert.equal(bundle.successor_observation.request, null);
      const actual = bundle.successor_observation.view.self_team.find((row) => row.name === 'Actual')!;
      assert.equal(actual.active, true); assert.equal(actual.item, 'leftovers');
      const terminal = new LocalBattleEnv(`incoming-restored-${actor}`, 'gen9randombattle', [1,2,3,4]);
      try {
        assert.equal(terminalSnapshot?.__neural_terminal_request_history.schema_version, 'terminal-request-history/v2');
        assert.ok(terminalSnapshot?.__neural_terminal_request_history.submitted_switches[actor]);
        const restoredTerminal = await terminal.resetFromSerialized(structuredClone(terminalSnapshot!));
        const owned = restoredTerminal.views[actor]!.self_team.find((row) => row.name === 'Actual')!;
        for (const field of ['active', 'item', 'hp_text', 'hp_ratio', 'last_item', 'item_state'] as const) assert.equal(owned[field], actual[field], field);
        for (const offset of [-1, 1, 100_000]) {
          const bad: Record<string, any> = structuredClone(terminalSnapshot!);
          bad.__neural_terminal_request_history.submitted_switches[actor].cursor += offset;
          const before: string = JSON.stringify(bad);
          await assert.rejects(terminal.resetFromSerialized(bad), /exact source choice boundary/);
          assert.equal(JSON.stringify(bad), before);
        }
        for (const mutation of ['downgraded-version', 'missing-switch-provenance', 'wrong-force-kind']) {
          const bad: Record<string, any> = structuredClone(terminalSnapshot!);
          if (mutation === 'downgraded-version') bad.__neural_terminal_request_history.schema_version = 'terminal-request-history/v1';
          else if (mutation === 'missing-switch-provenance') delete bad.__neural_terminal_request_history.submitted_switches;
          else bad.__neural_terminal_request_history.submitted_switches[actor].force_switch = true;
          const unchanged: string = JSON.stringify(bad);
          await assert.rejects(terminal.resetFromSerialized(bad), /v2 private history schema|historical owned action/);
          assert.equal(JSON.stringify(bad), unchanged);
        }
        const bad: Record<string, any> = structuredClone(terminalSnapshot!);
        const legal = bundle.input_observation.request!.legal_actions.actions.find((row) => row?.choice === 'switch 3')!;
        bad.__neural_terminal_request_history.submitted_switches[actor].action = canonicalActionFromLegalAction(bundle.input_observation.request!, legal.index);
        await assert.rejects(terminal.resetFromSerialized(bad), /source terminal owned base identity/);
      } finally {await terminal.close();}
      assert.equal(bundle.successor_observation.protocol_prefix.some((line) => line.startsWith(`|replace|${actor}a: `)), false);
      const observer = actor === 'p1' ? 'p2' : 'p1';
      const opposing = result.records[observer][0].successor_observation;
      assert.equal(opposing.view.opponent_team.some((row) => row.name === 'Actual'), false);
      assert.doesNotThrow(() => validatePipelineLinkedRecordBundle(JSON.parse(JSON.stringify(bundle))));
      const valid = python(bundle); assert.equal(valid.status, 0, valid.stderr);
      for (const mutation of ['move-instead', 'wrong-slot', 'foreign-player', 'alias', 'missing-owner', 'reorder', 'item'] as const) {
        const bad = structuredClone(bundle) as any;
        if (['move-instead', 'wrong-slot'].includes(mutation)) {
          const request = bad.input_observation.request;
          const choice = mutation === 'move-instead' ? 'move 1' : 'switch 3';
          const legal = request.legal_actions.actions.find((entry: any) => entry?.choice === choice)!;
          bad.action = canonicalActionFromLegalAction(request, legal.index);
          bad.transition.action_id = bad.action.action_id;
        } else if (mutation === 'foreign-player') {
          bad.action.player = observer;
          const fields = Object.fromEntries(Object.entries(bad.action).filter(([key]) => key !== 'action_id'));
          bad.action.action_id = `action-${digest(fields)}`; bad.transition.action_id = bad.action.action_id;
        } else if (mutation === 'alias') bad.successor_observation.view.self_team.find((row: any) => row.name === 'Actual').ident = `${actor}: Disguise`;
        else if (mutation === 'missing-owner') bad.successor_observation.view.self_team = bad.successor_observation.view.self_team.filter((row: any) => row.name !== 'Actual');
        else if (mutation === 'reorder') bad.successor_observation.view.self_team.reverse();
        else bad.successor_observation.view.self_team.find((row: any) => row.name === 'Actual').item = null;
        rehash(bad); itemIdentityMatrixCounts.ordinary++;
        assert.equal(python(bad, true).status, 0, mutation);
        const before = JSON.stringify(bad);
        assert.throws(() => validatePipelineLinkedRecordBundle(bad), /Public (health|item)|Canonical action/);
        const rejected = python(bad); assert.equal(rejected.status, 2, `${mutation}: ${rejected.stderr}`); assert.equal(rejected.stdout, '');
        assert.match(rejected.stderr, /Public (health|item)|canonical action/); assert.equal(JSON.stringify(bad), before);
      }
      if (schema.endsWith('v2')) {
        assert.doesNotThrow(() => validatePipelineEpisodeEvidence(result.evidence_envelope, result.records));
        for (const payload of [result, sweep(result)]) {const valid = python(payload); assert.equal(valid.status, 0, valid.stderr);}
        const bare = structuredClone(result.evidence_envelope);
        assert.throws(() => validatePipelineEpisodeEvidence(bare), /Public health.*sufficient owned identity authority/);
        const rejected = python(bare); assert.equal(rejected.status, 2, rejected.stderr); assert.equal(rejected.stdout, '');
        assert.throws(() => validateObservableBattleState(JSON.parse(JSON.stringify(bundle.successor_observation))), /Public health/);
        for (const mutation of ['move-instead', 'wrong-slot', 'missing-action', 'reorder', 'item']) {
          const bad = structuredClone(result) as any;
          const row = bad.records[actor][0];
          if (['move-instead', 'wrong-slot'].includes(mutation)) {
            const legal = row.input_observation.request.legal_actions.actions.find((entry: any) => entry?.choice === (mutation === 'move-instead' ? 'move 1' : 'switch 3'))!;
            row.action = canonicalActionFromLegalAction(row.input_observation.request, legal.index); row.transition.action_id = row.action.action_id;
          } else if (mutation === 'missing-action') delete row.action;
          else {
            const observation = bad.evidence_envelope.commits[0].boundary.perspectives[actor];
            if (mutation === 'reorder') observation.view.self_team.reverse();
            else observation.view.self_team.find((row: any) => row.name === 'Actual').item = null;
            row.successor_observation = structuredClone(observation); rehashResult(bad);
          }
          const before = JSON.stringify(bad);
          assert.throws(() => validatePipelineEpisodeEvidence(bad.evidence_envelope, bad.records), /Public (health|item)|action|undefined/);
          for (const [kind, payload] of [['fullResult', bad], ['sweep', sweep(bad)]] as const) {
            itemIdentityMatrixCounts[kind]++;
            const rejected = python(payload); assert.equal(rejected.status, 2, `${mutation}: ${rejected.stderr}`); assert.equal(rejected.stdout, '');
            assert.match(rejected.stderr, /Public (health|item)|action/);
          }
          assert.equal(JSON.stringify(bad), before);
          assert.throws(() => validateObservableBattleState(row.successor_observation), /Public health/);
        }
      }
    }
    const choices = actor === 'p1' ? ['switch 2', 'move 1'] : ['move 1', 'switch 2'];
    battle.makeChoices(...choices); restored.makeChoices(...choices);
    assert.equal(fingerprintSimulatorState(battle.toJSON()), fingerprintSimulatorState(restored.toJSON())); assert.equal(battle.ended, true);
  } finally {LocalBattleEnv.prototype.resetWithOptions = old; LocalBattleEnv.prototype.serializeBattle = oldSerialize; battle.destroy(); restored.destroy();}
});

// Constructed pinned-engine mechanic controls; these do not prove generated-team legality.
async function carrierEpisode(actor: PlayerID, shape: 'history' | 'frisk', schema = 'observable-battle-state/v2') {
  const own = shape === 'history'
    ? 'Eater (Zoroark) @ Sitrus Berry\nEVs: 4 HP\nAbility: Illusion\n- Belly Drum\n- Splash\n\nBench (Eevee)\nLevel: 1\nAbility: Run Away\n- Splash'
    : 'Actual (Zoroark) @ Leftovers\nAbility: Illusion\n- Splash\n\nBench (Eevee)\nAbility: Run Away\n- Splash\n\nDisguise (Snorlax) @ Sitrus Berry\nAbility: Immunity\n- Splash';
  const foe = shape === 'history' ? 'Target (Pikachu)\nLevel: 40\nAbility: Static\n- Quick Attack\n- Tackle' : 'Watcher (Dusknoir)\nAbility: Frisk\n- Splash';
  const battle = new Battle({formatid: 'gen9randombattle', seed: '1,2,3,4'});
  battle.setPlayer('p1', {name: 'One', team: Teams.import(actor === 'p1' ? own : foe)!});
  battle.setPlayer('p2', {name: 'Two', team: Teams.import(actor === 'p2' ? own : foe)!});
  const snapshot = structuredClone(battle.toJSON()), reset = LocalBattleEnv.prototype.resetWithOptions;
  try {
    LocalBattleEnv.prototype.resetWithOptions = function(options) {return this.resetFromSerialized(structuredClone(snapshot), options);};
    return await runPipelineEpisode({battle_id: `carrier-${actor}-${shape}-${schema}`, format: 'gen9randombattle', seed: [1,2,3,4],
      observation_schema_version: schema as any, limits: {max_transitions: shape === 'history' ? 4 : 2}, policy_id: 'carrier-attribution/v1',
      action_order: (observation) => {
        const choice = shape === 'frisk' ? observation.perspective === actor ? observation.view.turn === 1 ? 'switch 2' : 'move 1' : 'move 1'
          : observation.perspective !== actor ? observation.view.turn === 1 ? 'move 1' : 'move 2'
          : observation.request!.force_switch ? 'switch 2' : observation.view.turn === 1 ? 'move 1' : observation.view.turn === 3 ? 'move 2' : 'switch 2';
        const action = observation.request!.legal_actions.actions.find((entry) => entry?.choice === choice);
        assert.ok(action, choice); return [action.index, ...observation.request!.legal_actions.available_indices.filter((index) => index !== action.index)];
      }});
  } finally {LocalBattleEnv.prototype.resetWithOptions = reset; battle.destroy();}
}
for (const actor of ['p1', 'p2'] as const) {
  test(`carrier-specific ${actor} revealed consumption history rejects omission after re-entry`, async () => {
    for (const schema of ['observable-battle-state/v1', 'observable-battle-state/v2']) {
      const result = await carrierEpisode(actor, 'history', schema), original = structuredClone(result);
      assert.equal(result.counts.committed_transitions, 4, JSON.stringify(result.stop));
      const bundle = result.records[actor].at(-1)!;
      assert.ok(bundle.successor_observation.protocol_prefix.some((line) => line.startsWith(`|replace|${actor}a: Eater|`)));
      for (const player of ['p1', 'p2'] as const) for (const record of result.records[player]) {
        const valid = python(record); assert.equal(valid.status, 0, valid.stderr);
      }
      for (const which of ['input_observation', 'successor_observation'] as const) {
        const bad = structuredClone(bundle);
        const row = bad[which].view.self_team.find((entry) => entry.name === 'Eater')!;
        assert.equal(row.last_item, 'sitrusberry'); assert.equal(row.item_state, 'consumed');
        row.last_item = null; row.item_state = 'unknown'; rehash(bad);
        const identity = python(bad, true); assert.equal(identity.status, 0, identity.stderr);
        const before = structuredClone(bad);
        assert.equal(bad.schema_version, 'pipeline-linked-record/v1');
        assert.throws(() => validatePipelineLinkedRecordBundle(bad as any), /owned retained item history/);
        const invalid = python(bad); assert.equal(invalid.status, 2, invalid.stderr); assert.equal(invalid.stdout, '');
        assert.match(invalid.stderr, /owned retained item history/); assert.deepEqual(bad, before);
      }
      if (result.evidence_envelope) {
        const good = python(result); assert.equal(good.status, 0, good.stderr);
        const bad = structuredClone(result);
        const observation = bad.evidence_envelope!.commits.at(-1)!.boundary.perspectives[actor];
        const oldId = observation.observation_id, row = observation.view.self_team.find((entry) => entry.name === 'Eater')!;
        row.last_item = null; row.item_state = 'unknown';
        for (const record of bad.records[actor]) {
          if (record.input_observation.observation_id === oldId) record.input_observation = structuredClone(observation);
          if (record.successor_observation.observation_id === oldId) record.successor_observation = structuredClone(observation);
        }
        rehashResult(bad);
        for (const record of bad.records[actor]) assert.equal(python(record, true).status, 0);
        const before = structuredClone(bad);
        assert.throws(() => validatePipelineEpisodeEvidence(bad.evidence_envelope!, bad.records), /owned retained item history/);
        for (const payload of [bad, bad.evidence_envelope]) {
          const invalid = python(payload); assert.equal(invalid.status, 2, invalid.stderr); assert.equal(invalid.stdout, '');
          assert.match(invalid.stderr, /owned retained item history/);
        }
        assert.deepEqual(bad, before);
      }
      assert.deepEqual(result, original);
    }
  });
  test(`carrier-specific ${actor} departed unrevealed Frisk stays raw and owned possession stays authoritative`, async () => {
    const result = await carrierEpisode(actor, 'frisk');
    assert.equal(result.counts.committed_transitions, 2, JSON.stringify(result.stop));
    const observer = actor === 'p1' ? 'p2' : 'p1';
    const boundary = result.evidence_envelope!.commits[0].boundary;
    assert.ok(boundary.perspectives[actor].protocol_prefix.some((line) => line.startsWith(`|-item|${actor}a: Disguise|Leftovers|`)));
    assert.equal(boundary.perspectives[actor].protocol_prefix.some((line) => line.startsWith(`|replace|${actor}a:`)), false);
    assert.equal(boundary.perspectives[actor].view.self_team.find((entry) => entry.name === 'Actual')!.item, 'leftovers');
    assert.equal(boundary.perspectives[actor].view.self_team.find((entry) => entry.name === 'Disguise')!.item, 'sitrusberry');
    assert.equal(JSON.stringify(boundary.perspectives[observer].view).includes('"item":"leftovers"'), false);
    for (const player of ['p1', 'p2'] as const) for (const record of result.records[player]) {
      assert.equal(record.schema_version, 'pipeline-linked-record/v1'); validatePipelineLinkedRecordBundle(record as any); const valid = python(record); assert.equal(valid.status, 0, valid.stderr);
    }
    for (const payload of [result, result.evidence_envelope]) {const valid = python(payload); assert.equal(valid.status, 0, valid.stderr);}
    const replay = await carrierEpisode(actor, 'frisk'); assert.deepEqual(replay, result, 'restored continuation is deterministic');
  });
}
test('carrier-specific history preserves established teammate evidence across an ambiguous nickname collision', () => {
  const prefix = ['|switch|p1a: Real|Snorlax|100/100', '|replace|p1a: Real|Snorlax|100/100', '|-enditem|p1a: Real|Sitrus Berry|[eat]',
    '|switch|p1a: Bench|Eevee|100/100', '|switch|p1a: Real|Snorlax|100/100', '|-enditem|p1a: Real|White Herb', '|switch|p1a: Bench|Eevee|100/100'];
  const owners = [{ability: 'illusion', base_ability: 'illusion'}];
  assert.deepEqual(projectPublicOwnedItemHistory(prefix, 'p1', (target) => target, owners), {'p1: Real': {last_item: 'sitrusberry', item_state: 'consumed'}});
  const ambiguous = prefix.slice(3);
  assert.deepEqual(projectPublicOwnedItemHistory(ambiguous, 'p1', (target) => target, owners), {});
  const parity = spawnSync(process.env.PYTHON || 'python3', ['-c',
    'import json,sys; from neural.public_item import project_public_owned_item_history; data=json.load(sys.stdin); print(json.dumps([project_public_owned_item_history({"perspective":"p1","protocol_prefix":prefix,"request":{"side":data["owners"]},"view":{}}) for prefix in data["prefixes"]]))'],
    {input: JSON.stringify({prefixes: [prefix, ambiguous], owners}), encoding: 'utf8', timeout: 30_000});
  assert.equal(parity.status, 0, parity.stderr);
  assert.deepEqual(JSON.parse(parity.stdout), [{'p1: Real': {last_item: 'sitrusberry', item_state: 'consumed'}}, {}]);
});
